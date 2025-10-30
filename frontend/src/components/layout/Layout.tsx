import { FC, useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import Navbar from './Navbar';
import Sidebar from './Sidebar';
import { useAppDispatch, useAppSelector } from '@hooks';
import { fetchProjects } from '@store/slices/projectSlice';

const Layout: FC = () => {
  const dispatch = useAppDispatch();
  const { projects } = useAppSelector((state) => state.projects);

  useEffect(() => {
    dispatch(fetchProjects() as any);
  }, [dispatch]);

  return (
    <div className="flex h-screen bg-background">
      <Sidebar projects={projects} />
      <div className="flex flex-1 flex-col">
        <Navbar />
        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default Layout;
